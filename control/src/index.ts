import Fastify, { FastifyRequest } from 'fastify'
import cookie from '@fastify/cookie'
import Docker from 'dockerode'

const PASSWORD = process.env.ACCESS_PASSWORD ?? ''
const CONTAINER = process.env.NEKO_CONTAINER ?? 'mybrowse-neko'
// Deterministic token derived from the password — no DB needed
const TOKEN = Buffer.from(PASSWORD).toString('base64')

const app = Fastify({ logger: true })
const docker = new Docker({ socketPath: '/var/run/docker.sock' })

let lastSeen = Date.now()

// ── helpers ──────────────────────────────────────────────────────────────────

function authed(req: FastifyRequest): boolean {
  return (req.cookies as Record<string, string>).session === TOKEN
}

type ContainerState = 'running' | 'paused' | 'stopped'

async function containerState(): Promise<ContainerState> {
  try {
    const info = await docker.getContainer(CONTAINER).inspect()
    if (info.State.Paused) return 'paused'
    if (info.State.Running) return 'running'
  } catch (_e) { /* container missing or Docker unavailable */ }
  return 'stopped'
}

// ── HTML pages (inlined to stay dependency-free) ─────────────────────────────

function loginPage(): string {
  return /* html */`<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyBrowse</title>
<style>
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;
  justify-content:center;min-height:100vh;margin:0;background:#0f0f0f;color:#eee}
h1{font-size:1.4rem;margin:0 0 2rem}
.row{display:flex;gap:.5rem}
input{padding:.6rem 1rem;font-size:1rem;border:1px solid #444;background:#1a1a1a;
  color:#eee;border-radius:6px;width:220px;outline:none}
input:focus{border-color:#2563eb}
button{padding:.6rem 1.4rem;font-size:1rem;background:#2563eb;color:#fff;border:none;
  border-radius:6px;cursor:pointer}
button:hover{background:#1d4ed8}
.err{color:#f87171;margin-top:.75rem;font-size:.875rem;min-height:1.2em}
</style></head>
<body>
<h1>MyBrowse</h1>
<div class="row">
  <input type="password" id="pw" placeholder="Password" autofocus>
  <button onclick="go()">Enter</button>
</div>
<p class="err" id="err"></p>
<script>
async function go(){
  const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({password:document.getElementById('pw').value})});
  if(r.ok) location.href='/';
  else document.getElementById('err').textContent='Wrong password';
}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
</script>
</body></html>`
}

function statusPage(): string {
  return /* html */`<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyBrowse</title>
<style>
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;
  justify-content:center;min-height:100vh;margin:0;background:#0f0f0f;color:#eee;gap:1.25rem}
h1{font-size:1.4rem;margin:0}
.badge{padding:.25rem .75rem;border-radius:999px;font-size:.8rem;font-weight:600;letter-spacing:.03em}
.running{background:#16a34a1a;color:#4ade80;border:1px solid #16a34a40}
.paused {background:#ca8a041a;color:#fbbf24;border:1px solid #ca8a0440}
.stopped{background:#dc26261a;color:#f87171;border:1px solid #dc262640}
.btns{display:flex;gap:.75rem}
button{padding:.55rem 1.3rem;font-size:.95rem;border:none;border-radius:6px;cursor:pointer;
  transition:background .15s}
button:disabled{opacity:.35;cursor:default}
#btn-launch{background:#2563eb;color:#fff}#btn-launch:not(:disabled):hover{background:#1d4ed8}
#btn-pause {background:#374151;color:#eee}#btn-pause:not(:disabled):hover{background:#4b5563}
a{color:#60a5fa;font-size:.875rem;text-decoration:none}
a:hover{text-decoration:underline}
a.dim{opacity:.35;pointer-events:none}
.hint{font-size:.75rem;color:#6b7280;text-align:center;max-width:320px;line-height:1.5}
</style></head>
<body>
<h1>MyBrowse</h1>
<span class="badge stopped" id="badge">…</span>
<div class="btns">
  <button id="btn-launch" onclick="cmd('launch')">Launch</button>
  <button id="btn-pause"  onclick="cmd('pause')" disabled>Pause</button>
</div>
<a href="/neko/" target="_blank" rel="noopener" id="open-link" class="dim">Open browser →</a>
<p class="hint">Keep this tab open to prevent auto-pause after 60 s of inactivity.</p>
<script>
async function refresh(){
  const{state}=await(await fetch('/api/status')).json();
  const b=document.getElementById('badge');
  b.textContent=state; b.className='badge '+state;
  document.getElementById('btn-launch').disabled=state==='running';
  document.getElementById('btn-pause').disabled=state!=='running';
  const l=document.getElementById('open-link');
  l.className=state==='running'?'':'dim';
}
async function cmd(action){
  await fetch('/api/'+action,{method:'POST'});
  refresh();
}
// Heartbeat — keeps the container alive while this tab is open
setInterval(()=>fetch('/api/heartbeat',{method:'POST'}),30_000);
// Poll container state
setInterval(refresh,5_000);
refresh();
</script>
</body></html>`
}

// ── routes ────────────────────────────────────────────────────────────────────

async function main() {
  await app.register(cookie)

  // Called by Caddy forward_auth before every protected request
  app.get('/auth', async (req, reply) => {
    if (authed(req)) return reply.code(200).send()
    return reply.redirect('/login')
  })

  app.get('/login', async (req, reply) => {
    if (authed(req)) return reply.redirect('/')
    return reply.type('text/html').send(loginPage())
  })

  app.post('/login', {
    schema: {
      body: { type: 'object', properties: { password: { type: 'string' } }, required: ['password'] }
    }
  }, async (req: FastifyRequest<{ Body: { password: string } }>, reply) => {
    if (req.body.password !== PASSWORD) {
      return reply.code(401).send({ error: 'Wrong password' })
    }
    reply.setCookie('session', TOKEN, {
      httpOnly: true,
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 days
      sameSite: 'lax',
    })
    return reply.send({ ok: true })
  })

  app.get('/', async (_req, reply) => reply.type('text/html').send(statusPage()))

  // Heartbeat from the status page — resets the idle timer
  app.post('/api/heartbeat', async () => {
    lastSeen = Date.now()
    return { ok: true }
  })

  app.get('/api/status', async () => ({ state: await containerState() }))

  app.post('/api/launch', async () => {
    const s = await containerState()
    const c = docker.getContainer(CONTAINER)
    if (s === 'paused') await c.unpause()
    else if (s === 'stopped') await c.start()
    lastSeen = Date.now()
    return { ok: true }
  })

  app.post('/api/pause', async () => {
    if ((await containerState()) === 'running') {
      await docker.getContainer(CONTAINER).pause()
    }
    return { ok: true }
  })

  // Auto-pause: if no heartbeat for 60 s and container is running, pause it
  setInterval(async () => {
    if (Date.now() - lastSeen > 60_000 && (await containerState()) === 'running') {
      await docker.getContainer(CONTAINER).pause()
      app.log.info('auto-paused: no heartbeat for 60 s')
    }
  }, 10_000)

  await app.listen({ port: 3000, host: '0.0.0.0' })
}

main().catch(err => { console.error(err); process.exit(1) })

<template>
  <div class="landing-page landing-page-v4">
    <header class="site-header">
      <RouterLink class="brand" to="/" aria-label="OEDI-SI home">
        <img
          src="/landing/logos/oedi-si.png"
          alt="OEDI-SI"
          width="125"
          height="30"
        />
      </RouterLink>
      <nav aria-label="Landing page navigation">
        <RouterLink class="active" to="/" aria-current="page">Home</RouterLink>
        <RouterLink to="/read-more">Read More</RouterLink>
      </nav>
    </header>
    <main>
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy">
          <h1 id="hero-title">Skip the setup. Start testing.</h1>
          <p class="hero-summary">
            OEDI-SI is an open-source, flexible, and scalable co-simulation
            platform designed to accelerate the development, evaluation, and
            adoption of advanced power-system monitoring, control, and analysis
            technologies. It gives researchers, utilities, and industry
            collaborators a ready-to-run environment for exploring reproducible
            grid use cases&mdash; without requiring users to install or
            configure the underlying software environment.
          </p>
          <ul class="benefit-list" aria-label="Platform benefits">
            <li>No local installation</li>
            <li>Ready-to-run use cases</li>
            <li>Reproducible workflows</li>
          </ul>
          <div class="demo-video-frame">
            <video
              ref="demoVideo"
              class="demo-video"
              muted
              playsinline
              controls
              preload="metadata"
              aria-label="OEDI-SI platform demonstration"
            >
              <source src="/landing/oedi-si-demo.mp4" type="video/mp4" />
              Your browser does not support embedded video. You can
              <a href="/landing/oedi-si-demo.mp4"
                >download the OEDI-SI demonstration</a
              >
              instead.
            </video>
          </div>
        </div>
        <div class="access-column">
          <aside
            class="login-card workspace-card"
            aria-labelledby="workspace-card-title"
          >
            <div class="workspace-card-header">
              <p class="card-kicker">Run OEDI-SI</p>
              <h2 id="workspace-card-title">Choose your workspace</h2>
              <p class="workspace-intro">
                Use the hosted platform for the fastest start, or run OEDI-SI
                locally for development and customization.
              </p>
              <div
                class="workspace-tabs"
                role="tablist"
                aria-label="Choose how to run OEDI-SI"
              >
                <button
                  id="hosted-workspace-tab"
                  type="button"
                  role="tab"
                  :aria-selected="workspaceMode === 'hosted'"
                  aria-controls="hosted-workspace-panel"
                  :class="{ active: workspaceMode === 'hosted' }"
                  @click="workspaceMode = 'hosted'"
                >
                  <span>Hosted Platform</span>
                  <small
                    >Request an account and run OEDI-SI simulation here</small
                  >
                </button>
                <button
                  id="local-workspace-tab"
                  type="button"
                  role="tab"
                  :aria-selected="workspaceMode === 'local'"
                  aria-controls="local-workspace-panel"
                  :class="{ active: workspaceMode === 'local' }"
                  @click="workspaceMode = 'local'"
                >
                  <span>Local Machine</span>
                  <small>Running OEDI-SI at your local machine</small>
                </button>
              </div>
            </div>

            <div class="workspace-panel-stack">
              <div
                id="local-workspace-panel"
                class="local-workspace-panel"
                :class="{ active: workspaceMode === 'local' }"
                role="tabpanel"
                aria-labelledby="local-workspace-tab"
                :aria-hidden="workspaceMode !== 'local'"
              >
                <p class="card-kicker">Local workspace</p>
                <h3>Run OEDI-SI on your machine</h3>
                <p class="local-workspace-intro">Set up OEDI-SI locally to:</p>
                <ul class="local-workspace-actions">
                  <li>Download OEDI-SI</li>
                  <li>Explore the available use cases</li>
                  <li>Build your own use cases on your local machine</li>
                </ul>
                <a
                  class="workspace-resource-link"
                  href="https://openedi.github.io/oedisi/quickstart/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span>
                    <strong>Quick Start Guide</strong>
                    <small>Installation and local setup instructions</small>
                  </span>
                  <span aria-hidden="true">&#8599;</span>
                </a>
              </div>

              <div
                id="hosted-workspace-panel"
                class="hosted-workspace-panel"
                :class="{ active: workspaceMode === 'hosted' }"
                role="tabpanel"
                aria-labelledby="hosted-workspace-tab"
                :aria-hidden="workspaceMode !== 'hosted'"
              >
                <div v-if="checkingSession" class="login-loading" role="status">
                  <span class="spinner" aria-hidden="true"></span>Checking
                  workspace access...
                </div>
                <template v-else-if="session.authenticated">
                  <p class="card-kicker">Workspace access</p>
                  <h2 id="access-panel-title">Welcome back</h2>
                  <p class="login-description">
                    Signed in as <strong>{{ session.username }}</strong
                    >.
                  </p>
                  <a class="primary-button" href="/workspace">Open workspace</a>
                  <button class="text-button" type="button" @click="signOut">
                    Sign out
                  </button>
                </template>
                <template v-else>
                  <form role="tabpanel" @submit.prevent="signIn">
                    <p class="card-kicker">Workspace access</p>
                    <p class="login-description">
                      Use the account provided by the OEDI-SI team.
                    </p>
                    <label for="username">Username</label>
                    <input
                      id="username"
                      v-model.trim="username"
                      name="username"
                      type="text"
                      autocomplete="username"
                      autocapitalize="none"
                      spellcheck="false"
                      required
                    />
                    <label for="password">Password</label>
                    <input
                      id="password"
                      v-model="password"
                      name="password"
                      type="password"
                      autocomplete="current-password"
                      required
                    />
                    <p v-if="loginError" class="login-error" role="alert">
                      {{ loginError }}
                    </p>
                    <button
                      class="primary-button"
                      type="submit"
                      :disabled="signingIn"
                    >
                      <span
                        v-if="signingIn"
                        class="spinner small"
                        aria-hidden="true"
                      ></span>
                      {{ signingIn ? 'Signing in...' : 'Sign in' }}
                    </button>
                    <p class="login-support">
                      Need an account? Contact
                      <a v-if="supportEmail" :href="`mailto:${supportEmail}`">
                        {{ supportEmail }}
                      </a>
                      <span v-else>your deployment administrator</span>.
                    </p>
                    <a
                      class="workspace-resource-link hosted-tutorial-link"
                      href="https://openedi.github.io/oedisi/beginner/"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <span>
                        <strong>Platform Tutorial</strong>
                        <small
                          >Guidance for using the hosted OEDI-SI platform</small
                        >
                      </span>
                      <span aria-hidden="true">&#8599;</span>
                    </a>
                  </form>
                </template>
              </div>
            </div>
          </aside>
        </div>
      </section>
      <section class="survey-panel" aria-labelledby="survey-title">
        <a
          href="https://forms.cloud.microsoft/pages/responsepage.aspx?id=Q70920tMREWfigVT-fXyXrGVly7ORaRIvuuhX6DEfvdUNENIRk1EQUJJSzVVOFQ3TE84UElURDY1Si4u&amp;origin=lprLink&amp;route=shorturl"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span class="quick-resource-copy">
            <span id="survey-title" class="quick-resource-title"
              >User Feedback Survey</span
            >
            <span class="quick-resource-description">
              Share your OEDI-SI testing experience with the project team.
            </span>
          </span>
          <strong aria-hidden="true">&#8599;</strong>
        </a>
      </section>
      <section
        class="partner-strip"
        aria-label="Project support and participating laboratories"
      >
        <div class="supporting-organization">
          <p>Supported by</p>
          <img
            class="doe-logo"
            src="/landing/logos/doe.png"
            alt="United States Department of Energy"
            width="1350"
            height="387"
          />
        </div>
        <div class="partner-divider" aria-hidden="true"></div>
        <div class="developing-organizations">
          <p>Developed by</p>
          <div class="laboratory-logos">
            <img
              src="/landing/logos/anl.png"
              alt="Argonne National Laboratory"
              width="196"
              height="74"
            />
            <img
              src="/landing/logos/nlr.png"
              alt="National Laboratory of the Rockies"
              width="239"
              height="42"
            />
            <img
              src="/landing/logos/ornl.svg"
              alt="Oak Ridge National Laboratory"
              width="339"
              height="82"
            />
            <img
              src="/landing/logos/pnnl.png"
              alt="Pacific Northwest National Laboratory"
              width="242"
              height="123"
            />
          </div>
        </div>
      </section>
    </main>
    <footer>
      <p>Hosted for pilot testing by Oak Ridge National Laboratory.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { auth, type AuthStatus } from '@/lib/auth'
import '@/styles/landing.css'

const DEMO_HOLD_MS = 5000

const username = ref('')
const password = ref('')
const signingIn = ref(false)
const checkingSession = ref(true)
const loginError = ref('')
const workspaceMode = ref<'hosted' | 'local'>('hosted')
const supportEmail = import.meta.env.VITE_OEDISI_SUPPORT_EMAIL?.trim() ?? ''
const demoVideo = ref<HTMLVideoElement | null>(null)
const session = reactive<AuthStatus>({ authenticated: false })

let demoPlaybackTimer: number | undefined
let demoLoadedHandler: (() => void) | undefined

function setSession(next: AuthStatus) {
  session.authenticated = next.authenticated
  session.username = next.username
}

function clearDemoPlaybackTimer() {
  if (demoPlaybackTimer !== undefined) {
    window.clearTimeout(demoPlaybackTimer)
    demoPlaybackTimer = undefined
  }
}

function holdThenPlayDemo() {
  const video = demoVideo.value
  if (!video) return

  clearDemoPlaybackTimer()
  video.pause()
  video.currentTime = 0

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  demoPlaybackTimer = window.setTimeout(() => {
    demoPlaybackTimer = undefined
    void video.play().catch(() => {
      // Browser autoplay policies may require the user to start playback.
    })
  }, DEMO_HOLD_MS)
}

function initializeDemoPlayback() {
  const video = demoVideo.value
  if (!video) return

  video.addEventListener('ended', holdThenPlayDemo)
  video.addEventListener('play', clearDemoPlaybackTimer)
  video.addEventListener('pointerdown', clearDemoPlaybackTimer)

  if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
    holdThenPlayDemo()
  } else {
    demoLoadedHandler = holdThenPlayDemo
    video.addEventListener('loadedmetadata', demoLoadedHandler, { once: true })
  }
}

onMounted(async () => {
  initializeDemoPlayback()
  if (new URLSearchParams(window.location.search).get('login') === 'required') {
    loginError.value = 'Please sign in to continue.'
  }
  try {
    setSession(await auth.status())
  } catch {
    setSession({ authenticated: false })
  } finally {
    checkingSession.value = false
  }
})

onBeforeUnmount(() => {
  clearDemoPlaybackTimer()
  const video = demoVideo.value
  if (!video) return
  video.removeEventListener('ended', holdThenPlayDemo)
  video.removeEventListener('play', clearDemoPlaybackTimer)
  video.removeEventListener('pointerdown', clearDemoPlaybackTimer)
  if (demoLoadedHandler)
    video.removeEventListener('loadedmetadata', demoLoadedHandler)
})

async function signIn() {
  signingIn.value = true
  loginError.value = ''
  try {
    const next = await auth.login(username.value, password.value)
    password.value = ''
    setSession(next)
    window.location.assign('/workspace')
  } catch (error) {
    password.value = ''
    loginError.value =
      error instanceof Error ? error.message : 'Unable to sign in'
  } finally {
    signingIn.value = false
  }
}

async function signOut() {
  try {
    await auth.logout()
    setSession({ authenticated: false })
  } catch {
    loginError.value = 'Unable to sign out. Please try again.'
  }
}
</script>

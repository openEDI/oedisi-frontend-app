<template>
  <div class="landing-page read-more-page">
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
        <RouterLink to="/">Home</RouterLink>
        <RouterLink class="active" to="/read-more" aria-current="page"
          >Read More</RouterLink
        >
      </nav>
    </header>

    <main class="read-more-main">
      <section class="read-more-intro" aria-labelledby="read-more-title">
        <div class="section-heading">
          <p class="eyebrow">About OEDI-SI</p>
          <h1 id="read-more-title">
            From a promising idea to a meaningful experiment
          </h1>
          <a
            class="project-overview-link"
            href="https://openei.org/wiki/OEDI-SI/Overview"
            target="_blank"
            rel="noopener noreferrer"
          >
            Project Overview <span aria-hidden="true">&#8599;</span>
          </a>
        </div>
        <figure class="platform-figure">
          <img
            src="/landing/oedisi-capabilities-oedi-si-v2.png"
            alt="Four OEDI-SI platform pillars: flexible co-simulation, configurable what-if scenarios, scalability to large systems, and a data and algorithms repository."
            width="1938"
            height="812"
          />
          <figcaption>
            A modular environment for consistent, reproducible grid experiments.
          </figcaption>
        </figure>
      </section>

      <section
        class="read-more-capabilities"
        aria-labelledby="capabilities-title"
      >
        <div class="section-heading compact">
          <p class="eyebrow">What the platform enables</p>
          <h2 id="capabilities-title">Spend more time on the experiment</h2>
        </div>
        <div class="capability-grid">
          <article>
            <h3>Ready-to-run testing</h3>
            <p>
              Begin with curated use cases instead of rebuilding software
              environments.
            </p>
          </article>
          <article>
            <h3>Modular workflows</h3>
            <p>
              Plug in and exchange datasets, models, algorithms, and solvers.
            </p>
          </article>
          <article>
            <h3>Reproducible comparison</h3>
            <p>Repeat, modify, and share standardized analytical workflows.</p>
          </article>
          <article>
            <h3>Open, collaborative research</h3>
            <p>
              Evaluate and advance grid applications through collaboration among
              national laboratories, utilities, industry, and academia.
            </p>
          </article>
        </div>
      </section>
    </main>

    <footer>
      <RouterLink class="brand footer-brand" to="/" aria-label="OEDI-SI home">
        <img
          src="/landing/logos/oedi-si.png"
          alt="OEDI-SI"
          width="125"
          height="30"
        />
      </RouterLink>
      <p>Hosted for pilot testing by Oak Ridge National Laboratory.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import '@/styles/landing.css'
</script>

---
layout: default
title: Projects
permalink: /projects/
---

<section style="padding: 7rem 3rem 4rem;">
  <div class="section-header">
    <span class="section-label">ALL SYSTEMS</span>
    <div class="section-line"></div>
    <span class="section-sub">{{ site.data.projects | size }} ENTRIES</span>
  </div>

  <div class="projects-grid">
    {% for project in site.data.projects %}
    <div class="project-card project-card__status--{{ project.status }}">
      <div class="project-card__status project-card__status--{{ project.status }}">
        <span class="dot"></span>{{ project.status | upcase }}
      </div>
      <div class="project-card__title">{{ project.name }}</div>
      <div class="project-card__domain">{{ project.domain }}</div>
      <div class="project-card__desc">{{ project.description }}</div>
      <div class="project-card__tags">
        {% assign tags = project.stack | split: " / " %}
        {% for tag in tags %}
        <span class="project-card__tag">{{ tag }}</span>
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  </div>
</section>

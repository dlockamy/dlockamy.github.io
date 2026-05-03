---
layout: default
title: Blog
permalink: /blog/
---

<div class="archive">
  <div class="section-header">
    <span class="section-label">TRANSMISSION LOG</span>
    <div class="section-line"></div>
  </div>

  <ul class="archive__list">
    {% for post in site.posts %}
    <li class="archive__item">
      <span class="archive__date">{{ post.date | date: "%Y.%m.%d" }}</span>
      <span class="archive__title"><a href="{{ post.url | relative_url }}">{{ post.title }}</a></span>
      {% if post.ai_generated %}<span class="archive__ai-badge">AI</span>{% endif %}
    </li>
    {% endfor %}
  </ul>

  <p class="archive__rss">subscribe <a href="{{ '/feed.xml' | relative_url }}">via RSS</a></p>
</div>

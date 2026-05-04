# dlockamy.github.io

Personal portfolio and GitHub project index for Douglas Lockamy.

**Theme:** Mission Console — retro-futurist IBM mainframe aesthetic  
**Tagline:** *"My god, it's full of bits..."*

## Setup

```bash
# Install dependencies
bundle install

# Serve locally
bundle exec jekyll serve

# Build for production
bundle exec jekyll build
```

## Structure

```
.
├── _config.yml          # Site config, author info
├── _data/
│   ├── projects.yml     # All projects (populates console panels)
│   ├── skills.yml       # Skill bars
│   ├── readout.yml      # System readout panel
│   └── links.yml        # Uplink / contact links
├── _includes/
│   ├── nav.html
│   ├── footer.html
│   └── keyboard_row.html
├── _layouts/
│   ├── default.html
│   ├── home.html
│   ├── post.html
│   └── project.html
├── _sass/
│   └── _variables.scss  # Design tokens
├── assets/
│   ├── css/main.scss    # Full stylesheet
│   └── js/main.js       # Clock, GitHub API, animations
└── index.md             # Homepage bio content
```

## Updating Content

**Add a project:** Edit `_data/projects.yml`  
**Add a skill:** Edit `_data/skills.yml`  
**Update readout:** Edit `_data/readout.yml`  
**Update contact links:** Edit `_data/links.yml`

Projects in the `systems` category appear in Panel 1.  
Projects in the `web` category appear in Panel 2.

## GitHub Pages

Push to `main` branch — GitHub Actions will build and deploy automatically.

Custom domain: set `dlockamy.com` as the custom domain in repo Settings → Pages.

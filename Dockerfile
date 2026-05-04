FROM ruby:3.3-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /site

COPY Gemfile Gemfile.lock* ./
RUN bundle install

EXPOSE 4000 35729

# --force_polling is required for live-reload to work with Docker bind mounts on macOS
CMD ["bundle", "exec", "jekyll", "serve", \
     "--host", "0.0.0.0", \
     "--livereload", \
     "--force_polling"]

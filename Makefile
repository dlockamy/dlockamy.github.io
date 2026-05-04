IMAGE := dlockamy-site
PORT  := 4000

.PHONY: install build serve clean docker-build docker-serve

install:
	bundle install

build: install
	bundle exec jekyll build

serve: install
	bundle exec jekyll serve --livereload

clean:
	rm -rf _site .jekyll-cache

docker-build:
	docker build -t $(IMAGE) .

# Mounts the repo so edits are reflected without rebuilding the image.
# Note: local Jekyll version (4.x) differs from GitHub Pages (3.x).
docker-serve: docker-build
	docker run --rm -it \
		-p $(PORT):4000 \
		-p 35729:35729 \
		-v "$(PWD)":/site \
		$(IMAGE)

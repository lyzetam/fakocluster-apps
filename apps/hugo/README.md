# Fako Cluster Documentation Site

This is the Hugo-based documentation site for the Fako Cluster. It's designed to be built as a Docker image and deployed to Kubernetes.

## Structure

- `config.toml` - Hugo configuration
- `content/` - Documentation content (synced from main repo)
- `themes/` - Hugo themes (downloaded during build)
- `Dockerfile` - Multi-stage build for the site
- `nginx.conf` - Nginx configuration for serving the static site

## Building

```bash
docker build -t fako-docs:latest .
```

## Running Locally

```bash
# Run the built image
docker run -p 8080:80 fako-docs:latest

# Or run Hugo development server
hugo server -D
```

## Deployment

The image should be pushed to a container registry and then deployed to Kubernetes:

```yaml
image: your-registry/fako-docs:latest
```

## Content Sync

The content is synced from the main fako-cluster repository's `/docs` directory. This happens via:
1. GitHub webhook triggers build
2. Build process clones the main repo
3. Copies `/docs` to `/content`
4. Builds the static site
5. Packages with nginx

## Theme

Currently using the Docsy theme, which provides:
- Clean documentation layout
- Dark mode support
- Search functionality
- Mobile responsive design

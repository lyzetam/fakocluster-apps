# Build stage
FROM klakegg/hugo:ext-alpine AS builder

WORKDIR /src

# Install dependencies
RUN apk add --no-cache git npm

# Copy the Hugo configuration files
COPY config.toml .
COPY content/ /src/content/
COPY docs/ /src/content/docs/

# Download the theme and its dependencies
RUN npm install --save-dev autoprefixer postcss-cli postcss
RUN hugo mod init github.com/user/repo
RUN hugo mod get -u github.com/google/docsy
RUN hugo mod get -u github.com/twbs/bootstrap
RUN hugo mod get -u github.com/FortAwesome/Font-Awesome

# Build the Hugo site
RUN hugo --minify --baseURL https://blog.landryzetam.net

# Runtime stage - using nginx to serve static files
FROM nginx:alpine

# Copy the built site from builder
COPY --from=builder /src/public /usr/share/nginx/html

# Copy custom nginx config if needed
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

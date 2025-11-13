# Custom Nginx image with embedded configuration
# Note: This is optional. The simpler approach is to use official nginx:alpine
# and volume-mount nginx.conf. This Dockerfile is only needed if you want to
# bake configuration into the image.

FROM nginx:alpine

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove default config if exists
RUN rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Create directories for cache and logs
RUN mkdir -p /var/cache/nginx /var/log/nginx && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Default command
CMD ["nginx", "-g", "daemon off;"]


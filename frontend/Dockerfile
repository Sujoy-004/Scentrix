FROM node:20-alpine

WORKDIR /app

# Copy package files relative to the root context
COPY frontend/package*.json ./

# Install all dependencies
RUN npm install

# Copy source code relative to the root context
COPY frontend/ .

EXPOSE 3000

# Default to dev mode for local environment.
CMD ["npm", "run", "dev"]

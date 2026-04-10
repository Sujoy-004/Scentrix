FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDeps for next dev)
RUN npm install

# Copy source code
COPY . .

EXPOSE 3000

# Default to dev mode for local environment.
# Note: docker-compose overrides this with npm run dev.
CMD ["npm", "run", "dev"]

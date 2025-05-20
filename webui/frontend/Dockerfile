# Use official Node.js image as the base
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
COPY vite.config.js ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "start"]

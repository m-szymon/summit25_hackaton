# Use official Node.js image as the base
FROM node:20-alpine
RUN apk add --no-cache gettext
RUN npm install -g @angular/cli
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 4200
ENTRYPOINT ["/app/start.sh"]

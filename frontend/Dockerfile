# Usa una imagen de Node.js
FROM node:20 AS build-stage
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm install


EXPOSE 8080
CMD ["npm", "run", "dev"]
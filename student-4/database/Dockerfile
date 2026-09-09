#FROM node:20-alpine
#
#WORKDIR /app
#
#COPY package*.json ./
#
#RUN npm ci
#
#COPY . .
#
#EXPOSE 5002
#
#CMD ["npm", "start"]


FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache python3 make g++

COPY package*.json ./

RUN npm ci

COPY . .

EXPOSE 5002

CMD ["npm", "start"]
FROM node:21.7.3-slim

RUN mkdir /app && chown node:node /app
RUN mkdir -p /usr/build/dist && chown -R node:node /usr/build/dist
WORKDIR /app

USER node

COPY --chown=node:node ./front/package.json ./front/yarn.lock ./
RUN yarn install


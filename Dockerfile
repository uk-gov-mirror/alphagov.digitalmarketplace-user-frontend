FROM digitalmarketplace/builder as builder

COPY requirements.txt ${APP_DIR}
RUN ${APP_DIR}/venv/bin/pip3 install --no-cache-dir -r requirements.txt

COPY package.json package-lock.json ${APP_DIR}/
RUN npm ci

COPY . ${APP_DIR}

RUN npm run frontend-build:production

FROM digitalmarketplace/base-frontend:9.0.0-alpha

COPY --from=builder ${APP_DIR} ${APP_DIR}

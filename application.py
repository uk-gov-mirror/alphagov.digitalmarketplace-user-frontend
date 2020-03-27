#!/usr/bin/env python

import os
import redis
from app import create_app
from flask_session import Session
from dmutils import init_manager

application = create_app(os.getenv('DM_ENVIRONMENT') or 'development')

application.config.from_object(__name__)
application.config['SESSION_REDIS'] = redis.from_url('redis://127.0.0.1:6379')
sess = Session()
sess.init_app(application)

manager = init_manager(application, 5007)

if __name__ == '__main__':
    manager.run()

#!/bin/bash
gunicorn -b 0.0.0.0:5001 main:app

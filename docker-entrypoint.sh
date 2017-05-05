#!/bin/bash


cd /app
factored_initializedb $CONFIG
pserve $CONFIG

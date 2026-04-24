#!/bin/bash
# Starts the local ollama server and forces it to save models in the Ken folder
export OLLAMA_MODELS="./ollama_models"
./ollama_cmd serve

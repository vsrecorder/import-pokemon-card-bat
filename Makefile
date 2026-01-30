SHELL := /bin/bash

.PHONY: source-bash
source-bash:
	bash --rcfile <(echo "source ~/.bashrc; python3 -m venv .venv; source .venv/bin/activate")
	#bash -c "python3 -m venv .venv; source .venv/bin/activate; exec bash -i"

.PHONY: source-fish
source-fish:
	fish -C "python3 -m venv .venv; source .venv/bin/activate.fish"

.PHONY: pipi
pipi:
	pip install -r requirements.txt

.PHONY: run
run:
	python3 main.py

.PHONY: dump
dump:
	pg_dump  -U vsrecorder -h localhost -t pokemon_cards -a > dump/pokemon_cards.dump

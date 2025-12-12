.PHONY: source
source:
	fish -C "python3 -m venv .ven; source .venv/bin/activate.fish

.PHONY: run
run:
	python3 main.py

.PHONY: dump
dump:
	pg_dump  -U vsrecorder -h localhost -t pokemon_cards -a > dump/pokemon_cards.dump

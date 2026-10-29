install:
	python -m pip install -r requirements.txt
test:
	python -m pytest -q
web:
	python -m rnjob web
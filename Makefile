.PHONY: setup test verify build demo doctor live-doctor

setup:
	bash scripts/setup.sh

test:
	bash scripts/test.sh

verify:
	bash scripts/test.sh --full

build:
	cd dashboard && npm run build

demo:
	bash scripts/demo.sh

doctor:
	python3 scripts/doctor.py

live-doctor:
	python3 scripts/doctor.py --live

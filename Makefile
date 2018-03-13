build: build-validator build-authenticator

test: test-validator test-authenticator test-factored

run:
	docker-compose run --rm --service-ports nginx


build-validator:
	docker-compose build fvalidator
build-authenticator:
	docker-compose build fauth

test-validator:
	docker-compose run --no-deps --rm --service-ports fvalidator py.test factored/validator/tests.py
test-authenticator:
	docker-compose run --no-deps --rm --service-ports fvalidator py.test factored/authenticator/tests.py
test-factored:
	docker-compose run --no-deps --rm --service-ports fvalidator py.test factored/tests.py

run-validator:
	docker-compose run --no-deps --rm --service-ports fvalidator
run-validator-bash:
	docker-compose run --no-deps --rm --service-ports fvalidator /bin/bash
run-debugmailer:
	docker-compose up --build --remove-orphans debugmailer

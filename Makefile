serve:
	panel serve Dashboard.py --prefix analogs --autoreload --log-level=debug --static-dirs fonts=./fonts

profile:
	panel serve Dashboard.py --prefix analogs --autoreload --log-level=debug --admin --profiler snakeviz --static-dirs fonts=./fonts

build-local:
	docker build --target base    -t analogues-spatiaux-en:dev .
	docker build --target base-fr -t analogues-spatiaux-fr:dev .
	
run-local:
	docker run -p 5006:5006 -d -e BOKEH_ALLOW_WS_ORIGIN=* analogues-spatiaux-en:dev
	docker run -p 5007:5006 -d -e BOKEH_ALLOW_WS_ORIGIN=* analogues-spatiaux-fr:dev

rm-local:
	CONTAINER_NAME="$(shell docker ps -a -q --filter ancestor='analogues-spatiaux-en:dev' --format="{{.ID}}")";docker stop $$CONTAINER_NAME;docker rm $$CONTAINER_NAME
	CONTAINER_NAME="$(shell docker ps -a -q --filter ancestor='analogues-spatiaux-fr:dev' --format="{{.ID}}")";docker stop $$CONTAINER_NAME;docker rm $$CONTAINER_NAME

build-test:
	docker build -t analogues-spatiaux:test-locust ./test/test_locust
	docker build -t analogues-spatiaux:test-loadwright ./test/test_loadwright

run-test-locust:
	docker run -d -p 8089:8089 analogues-spatiaux:test-locust

run-test-loadwright:
	docker run -d  analogues-spatiaux:test-loadwright

rm-test:
	CONTAINER_NAME="$(shell docker ps -a -q --filter ancestor='analogues-spatiaux:test-locust' --format="{{.ID}}")";docker stop $$CONTAINER_NAME;docker rm $$CONTAINER_NAME
	CONTAINER_NAME="$(shell docker ps -a -q --filter ancestor='analogues-spatiaux:test-loadwright' --format="{{.ID}}")";docker stop $$CONTAINER_NAME;docker rm $$CONTAINER_NAME

build-release:
	docker build -t registry.gitlab.com/crim.ca/clients/ccdp/analogues-spatiaux:dev .

push-release:
	docker push registry.gitlab.com/crim.ca/clients/ccdp/analogues-spatiaux:dev

deploy-staging:
	IAC_CONFIG=/home/grol/venv/ccdp/analogues-spatiaux-iac/base.yaml,/home/grol/venv/ccdp/analogues-spatiaux-iac/staging.yaml IAC_ENV_LOCAL_FILE=/mnt/c/Users/gruweol/.iac-openstack/env.local make -C ../../iac-openstack iac-update-stack

deploy-prod:
	IAC_CONFIG=/home/grol/venv/ccdp/analogues-spatiaux-iac/base.yaml,/home/grol/venv/ccdp/analogues-spatiaux-iac/prod.yaml IAC_ENV_LOCAL_FILE=/mnt/c/Users/gruweol/.iac-openstack/env.local make -C ../../iac-openstack iac-update-stack

build-deploy-staging:
	$(MAKE) build-release
	$(MAKE) push-release
	$(MAKE) deploy-staging

build-deploy-prod:
	$(MAKE) build-release
	$(MAKE) push-release
	$(MAKE) deploy-prod

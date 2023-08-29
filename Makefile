serve:
	panel serve Dashboard.py --prefix analogs --autoreload --log-level=debug --static-dirs fonts=./fonts

profile:
	panel serve Dashboard.py --prefix analogs --autoreload --log-level=debug --admin --profiler snakeviz --static-dirs fonts=./fonts

build-local:
	docker build -t analogues-spatiaux:dev .

run-local:
	docker run -p 5006:5006 -d -e BOKEH_ALLOW_WS_ORIGIN=127.0.0.1:5006,localhost:5006 analogues-spatiaux:dev

rm-local:
	CONTAINER_NAME="$(shell docker ps -a -q --filter ancestor='analogues-spatiaux:dev' --format="{{.ID}}")";docker stop $$CONTAINER_NAME;docker rm $$CONTAINER_NAME

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
	IAC_CONFIG=../analogues-spatiaux-iac/base.yaml,../analogues-spatiaux-iac/staging.yaml make -C ../iac-openstack iac-update-stack

deploy-prod:
	IAC_CONFIG=../analogues-spatiaux-iac/base.yaml,../analogues-spatiaux-iac/prod.yaml make -C ../iac-openstack iac-update-stack

build-deploy-staging:
	$(MAKE) build-release
	$(MAKE) push-release
	$(MAKE) deploy-staging

build-deploy-prod:
	$(MAKE) build-release
	$(MAKE) push-release
	$(MAKE) deploy-prod

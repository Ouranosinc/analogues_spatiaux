serve:
	panel serve Dashboard.ipynb --prefix analogs --autoreload --log-level=debug

profile:
	panel serve Dashboard.ipynb --prefix analogs --autoreload --log-level=debug --admin --profiler snakeviz

build-local:
	docker build -t analogues-spatiaux:dev .

run-local:
	docker run -p 5006:5006 -e BOKEH_ALLOW_WS_ORIGIN=127.0.0.1:5006,localhost:5006 analogues-spatiaux:dev

build-release:
	docker build -t registry.gitlab.com/crim.ca/clients/ccdp/analogues-spatiaux:dev .

push-release:
	docker push registry.gitlab.com/crim.ca/clients/ccdp/analogues-spatiaux:dev

deploy-staging:
	IAC_CONFIG=../analogues-spatiaux-iac/staging.yaml make -C ../iac-openstack iac-recreate-vm

build-deploy:
	$(MAKE) build-release
	$(MAKE) push-release
	$(MAKE) deploy-staging

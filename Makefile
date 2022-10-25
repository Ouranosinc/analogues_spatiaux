serve:
	panel serve Dashboard.ipynb --prefix analogues_spatiaux --autoreload --log-level=debug

build-local:
	docker build -t analogues-spatiaux:dev ../analogues_spatiaux

run-local:
	docker run -p 5006:5006 -e BOKEH_ALLOW_WS_ORIGIN=127.0.0.1:5006,localhost:5006 analogues-spatiaux:dev

build-release:
	docker build -t registry.gitlab.com/crim.ca/clients/ccdp/analogues-spatiaux:dev ../analogues_spatiaux

push-release:
	docker push registry.gitlab.com/crim.ca/clients/ccdp/analogues-spatiaux:dev

deploy-staging:
	IAC_CONFIG=../analogues-spatiaux-iac/staging.yaml make -C ../iac-openstack iac-recreate-vm

build-deploy:
	$(MAKE) build-release
	$(MAKE) push-release
	$(MAKE) deploy-staging

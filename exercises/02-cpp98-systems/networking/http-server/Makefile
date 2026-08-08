.PHONY: observe exercise-test test failure-test clean
observe:
	@$(MAKE) -C 01-parser observe
	@$(MAKE) -C 02-config-router observe
	@$(MAKE) -C 03-nonblocking-server observe
	@$(MAKE) -C 04-cgi-process observe
	@$(MAKE) -C 05-integrated-server observe
exercise-test:
	@$(MAKE) -C 01-parser exercise-test
	@$(MAKE) -C 02-config-router exercise-test
	@$(MAKE) -C 03-nonblocking-server exercise-test
	@$(MAKE) -C 04-cgi-process exercise-test
	@$(MAKE) -C 05-integrated-server exercise-test
test:
	@$(MAKE) -C 01-parser test
	@$(MAKE) -C 02-config-router test
	@$(MAKE) -C 03-nonblocking-server test
	@$(MAKE) -C 04-cgi-process test
	@$(MAKE) -C 05-integrated-server test
failure-test:
	@$(MAKE) -C 01-parser failure-test
	@$(MAKE) -C 02-config-router failure-test
	@$(MAKE) -C 03-nonblocking-server failure-test
	@$(MAKE) -C 04-cgi-process failure-test
	@$(MAKE) -C 05-integrated-server failure-test
clean:
	@$(MAKE) -C 01-parser clean
	@$(MAKE) -C 02-config-router clean
	@$(MAKE) -C 03-nonblocking-server clean
	@$(MAKE) -C 04-cgi-process clean
	@$(MAKE) -C 05-integrated-server clean

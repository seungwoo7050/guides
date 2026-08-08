.PHONY: observe exercise-test test randomized-test clean
observe:
	@$(MAKE) -C date-lookup observe
	@$(MAKE) -C rpn observe
	@$(MAKE) -C sorter observe
exercise-test:
	@$(MAKE) -C date-lookup exercise-test
	@$(MAKE) -C rpn exercise-test
	@$(MAKE) -C sorter exercise-test
test:
	@$(MAKE) -C date-lookup test
	@$(MAKE) -C rpn test
	@$(MAKE) -C sorter test
randomized-test:
	@$(MAKE) -C sorter randomized-test
clean:
	@$(MAKE) -C date-lookup clean
	@$(MAKE) -C rpn clean
	@$(MAKE) -C sorter clean

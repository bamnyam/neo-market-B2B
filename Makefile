SERVICES = B2B B2C

test:
	@for service in $(SERVICES); do \
		echo "Running tests for $$service..."; \
		$(MAKE) -C $$service test; \
	done

lint:
	@for service in $(SERVICES); do \
		echo "Running lint for $$service..."; \
		$(MAKE) -C $$service lint; \
	done

format:
	@for service in $(SERVICES); do \
		echo "Running format for $$service..."; \
		$(MAKE) -C $$service format; \
	done

check: lint test
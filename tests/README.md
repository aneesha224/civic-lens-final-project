# Tests

Run the credential-free checks from the Final Project directory:

`.venv/bin/python -m unittest discover -s tests`

The focused safety demonstration runs without a model key:

`.venv/bin/python -m unittest discover -s tests -p 'test_safety.py'`

It verifies that the workflow removes a fabricated quotation while retaining an
exact excerpt from the selected source. The full suite has not been run for this
report snapshot. Further evaluations should cover prompt-injection behavior,
provider failure, and deployed request quotas.


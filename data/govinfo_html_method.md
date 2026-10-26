# GovInfo HTML source method

GovInfo publishes individual Congressional Record pages as HTML files with the original page text inside a `<pre>` element. These pages are more useful for the app than a full PDF because they can be fetched on demand and retain an official, stable source URL.

Each row in `speech_records.csv` now has a `govinfo_html_candidate_url` field. The local PDF and extracted text remain the archival copy used for verification. A future ingestion step must fetch the candidate page, confirm that its printed page label and speaker text match the record, then preserve the `<pre>` text exactly. It must fall back to the PDF when the HTML page is unavailable or does not match.

The current links use the `pt1` path used by the tested January 8, 2020 package. The ingestion code should test `pt1` and `pt2` when a package uses multiple parts and record which URL returned the text.


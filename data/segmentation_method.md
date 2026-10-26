# Speaker segmentation method

`segment_speaker_remarks.py` takes each page-level transcript and finds the selected politician’s Congressional Record speaker heading. It copies text from that heading until the next speaker heading on the same page. The original page transcript remains available, and every segmented record stores character offsets into that original file.

The output is an exact source substring. It is not a cleaned-up transcript, summary, or AI-generated reconstruction. Some pages may remain `unsegmented` when the PDF extraction does not expose a recognizable heading; those records remain usable through the original source page and should be reviewed before analysis.


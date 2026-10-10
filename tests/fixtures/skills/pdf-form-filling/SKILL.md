---
name: pdf-form-filling
description: Fill in PDF forms programmatically. Reads AcroForm field names, writes values, flattens the result and checks the output renders.
---

# PDF form filling

## List the fields
Open the PDF with a library such as pypdf and print every field name and type before
writing anything. Field names are rarely what the printed label says.

## Write the values
Set text fields by name, tick checkboxes with the exact "on" value the form defines, and
choose radio buttons by their export value.

## Flatten
Flatten the form when the file goes to someone else, so the values cannot be edited.
Render page one to an image and look at it before sending.

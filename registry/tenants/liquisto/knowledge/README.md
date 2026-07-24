# Olivia runtime knowledge

This directory contains only small, reviewed baseline facts for Olivia. It must
not contain secrets, credentials, production records, unfiltered employee data,
or copied knowledge from another tenant.

The complete `liquisto.cloud` architecture and internal-system context remain
owned by their source repositories and systems. SCAS must authenticate the
employee, enforce their permissions and purpose, and pass only bounded context
items with source, permission, classification, and observation metadata to the
v2 assistant contract. The runtime then checks every item against the active
`data_sources` contract in `tenant.json`; planned, unknown, mismatched, or
write-capable sources fail closed. The runtime has no direct connector or write
authority.

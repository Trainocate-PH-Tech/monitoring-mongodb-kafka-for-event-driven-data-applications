# mongo-express Slow-Query Imports

These files are ready-to-import Extended JSON arrays for Section 19 of
[`MONGODB_EXPRESS_GUIDE.md`](../../MONGODB_EXPRESS_GUIDE.md#19-slow-query-management).
Each file contains 50,000 deterministic documents and must be imported into the
collection with the same base name.

Importing appends documents. Create an empty collection with only its automatic
`_id_` index before uploading a file through mongo-express.

To regenerate all five files from the repository root:

```bash
node mongodb/generate-slow-query-imports.mjs
```

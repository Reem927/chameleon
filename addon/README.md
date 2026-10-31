# Chameleon Viewer (Adobe Express add-on)

The viewer add-on the stage-one submission asks for (FAQ Q5). It is required but not scored.

Owner: Reem.

It opens inside Adobe Express as a panel:

1. Pick an engine output JSON and its rendered PNG from `output/`.
2. The panel shows the canvas size, the element count and the PNG size, plus a preview.
3. **Add image to document** places the rendered PNG on the current Express page, unchanged.

It reads only the files you pick. It makes no network calls of its own and never edits pixels.

Scaffolded with Adobe's `npx @adobe/create-ccweb-add-on chameleon-viewer --template javascript`.

## Not part of the scored engine

The root `Dockerfile` copies only `engine/`, `renderer/`, `brand_kit/` and the schema, so nothing here enters the Docker image.
`engine/` never imports it.

## Build and run

Needs Node 18 or later.

```bash
cd addon
npm ci
npm run build     # writes dist/
npm run package   # writes dist.zip for upload to Express
npm run start     # serves https://localhost:5241 for Express developer mode
```

`npm run start` asks once how to set up a local SSL certificate.
Then load `https://localhost:5241` in Adobe Express developer mode, following Adobe's add-on developer docs.

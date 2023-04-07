const fs = require("fs");
const path = require("path");
const cp = require("child_process");

const express = require("express");
const { default: axios } = require("axios");

const multipart = require("connect-multiparty")();

const app = express();
app.use(express.static(path.resolve(__dirname, "public")));
app.use("/icon", express.static(path.resolve(__dirname, "template")));
app.post("/check", multipart, async (req, res) => {
	const inp = req.files.file.path;
	let ret = "";

	let t = Date.now();
	await new Promise(r => {
		const p = cp.exec(`py ./main.py "${inp}"`);
		p.once("exit", () => r());
		p.stdout.on("data", data => (ret += data));
	});
	console.log(`checked in ${Date.now() - t} msec`);

	fs.unlinkSync(inp); // remove uploaded file

	res.send(JSON.parse(ret));
});
app.get("/locale", (req, res) => {
	let lang = req.query.lang;
	if (!["KR", "EN", "JP", "TC", "SC"].includes(lang))
		lang = "KR";

	axios.get(`https://lo.swaytwig.com/json/locale/${lang}.json?_=${Math.floor(Date.now() / 3600000)}`)
		.then(r => {
			const locale = {};
			Object.keys(r.data).forEach(k => {
				if (k.startsWith("EQUIP_Sub_") || k.startsWith("EQUIP_System_") || k.startsWith("EQUIP_Chip_"))
					locale[k] = r.data[k];
			});

			res.send(locale);
		});
});
app.listen(8088, () => {
	console.log("Listen on localhost:8088");
});

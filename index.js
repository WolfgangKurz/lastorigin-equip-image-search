const fs = require("fs");
const path = require("path");
const cp = require("child_process");

const YAML = require("yaml");

const express = require("express");
const { default: axios } = require("axios");

const multipart = require("connect-multiparty")();

const PORT = 50375;

const locales = {};

const app = express();
app.use(express.static(path.resolve(__dirname, "public")));
app.use("/icon", express.static(path.resolve(__dirname, "template")));
app.post("/check", multipart, async (req, res) => {
    const inp = req.files.file.path;
    let ret = "";

    let t = Date.now();
    await new Promise(r => {
        const p = cp.exec(`python3 ./main.py "${inp}"`);
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

    if (lang in locales) {
        res.send(locales[lang]);
        return;
    }

    axios.get(`https://lo.swaytwig.com/yaml/locale/${lang}.yml?_=${Math.floor(Date.now() / 3600000)}`)
        .then(y => {
            const r = YAML.parse(y.data);
            const locale = {};
            Object.keys(r).forEach(k => {
                if (k.startsWith("EQUIP_Sub_") || k.startsWith("EQUIP_System_") || k.startsWith("EQUIP_Chip_"))
                    locale[k] = r[k];
            });

            locales[lang] = locale;
            res.send(locale);
        });
});
app.listen(PORT, () => {
    console.log("Listen on localhost:PORT");
});

"use static";
(() => {
	const input = document.querySelector("#screenshot");
	const preview = document.querySelector("#preview");
	const content = document.querySelector("#main");
	let locale = {};

	const lang = (() => {
		const lang = window.navigator.userLanguage || window.navigator.language;
		const langp = lang.split("-")[0].toLowerCase();
		switch (langp) {
			case "ja":
				return "JP";
			case "en":
				return "EN";
			case "ko":
				return "KR";

			default:
				if (lang.startsWith("zh-Hant"))
					return "TC";
				else if (lang.startsWith("zh-Hans"))
					return "SC";
				return "KR";
		}
	})();

	function conv (m) {
		const k = `EQUIP_${m}`;
		if (k in locale) {
			// const tier = m.replace(/^.+_T([0-9]+)$/, "$1");
			// const tiers = ["?", "RE", "MP", "SP", "EX", "SSS"];
			// return `${locale[k]}  ${tiers[tier]}`;
			return locale[k];
		}
		return m;
	}

	input.addEventListener("change", () => {
		if (input.files.length <= 0) return;
		input.disabled = true;

		new Promise((resolve, reject) => {
			const img = new Image();
			const url = URL.createObjectURL(input.files[0]);
			img.src = url;
			img.addEventListener("load", () => {
				URL.revokeObjectURL(url);
				resolve(img);
			});
			img.removeEventListener("error", e => {
				URL.revokeObjectURL(url);
				reject(e);
			});
		})
			.then(async img => {
				const cv = document.createElement("canvas");
				cv.width = img.naturalWidth;
				cv.height = img.naturalHeight;

				const ctx = cv.getContext("2d");
				ctx.drawImage(img, 0, 0);

				const cv2 = document.createElement("canvas");
				const ctx2 = cv2.getContext("2d");

				const blob = await new Promise(r => cv.toBlob(b => r(b), "image/jpeg", 0.75));

				const previewURL = URL.createObjectURL(blob);
				preview.className = "loading";
				preview.src = previewURL;

				content.querySelectorAll(".parsed").forEach(el => el.remove());

				const body = new FormData();
				body.append("file", blob);

				return fetch("/check", {
					method: "POST",
					body,
				})
					.then(r => r.json())
					.then(r => {
						if (!r.result) {
							alert(r.message);
							return;
						}

						cv.width /= r.scale;
						cv.height /= r.scale;
						ctx.drawImage( // redraw with scale value
							img,
							0, 0, img.naturalWidth, img.naturalHeight,
							0, 0, cv.width, cv.height,
						);

						r.data.forEach(d => {
							const _parsed = document.createElement("div");
							_parsed.className = "parsed";

							const _slots = new Image();
							_slots.className = "slots";
							_parsed.appendChild(_slots);

							const _rect = document.createElement("div");
							_rect.className = "rect";
							_rect.innerText = JSON.stringify(d.parsed);
							_parsed.appendChild(_rect);

							cv2.width = d.parsed.w;
							cv2.height = d.parsed.h;
							ctx2.drawImage(
								cv,
								d.parsed.x, d.parsed.y, d.parsed.w, d.parsed.h,
								0, 0, d.parsed.w, d.parsed.h,
							);
							_slots.src = cv2.toDataURL();

							d.matched.forEach((m, mi) => {
								const _slot = document.createElement("div");
								_slot.className = "slot";

								const _icon = new Image();
								if (!m)
									_icon.dataset["empty"] = "1";
								else
									_icon.src = `/icon/UI_Icon_Equip_${m}.png`;

								_slot.appendChild(_icon);

								const _text = document.createElement("a");
								_slot.appendChild(_text);
								_text.title = m;
								if (!m) {
									_text.addEventListener("click", e => e.preventDefault());
									_text.innerText = "Empty slot";
								} else {
									_text.target = "_blank";
									_text.href = `https://lo.swaytwig.com/equips/${m}`;
									_text.innerText = conv(m);
								}

								const _score = document.createElement("span");
								_slot.appendChild(_score);
								if (m)
									_score.innerText = d.score[mi];

								_parsed.append(_slot);
							});

							content.appendChild(_parsed);
						});
					})
					.finally(() => {
						cv.remove();
						cv2.remove();

						if (preview.src) {
							URL.revokeObjectURL(preview.src);
							preview.className = "";
							preview.src = "";
						}
					});
			})
			.catch(e => {
				alert("Failed to load image, maybe not readable.");
			})
			.finally(() => {
				input.disabled = false;
			});
	});

	fetch(`/locale?lang=${lang}&_=${Math.floor(Date.now() / 3600000)}`)
		.then(r => r.json())
		.then(r => (locale = r));
})();

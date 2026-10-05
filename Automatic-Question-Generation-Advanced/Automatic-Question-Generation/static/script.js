const $ = (id) => document.getElementById(id);
const text = $("text"), go = $("go"), list = $("list");
const EXAMPLE = "Photosynthesis is the process by which green plants convert light energy into chemical energy. " +
  "Chlorophyll, found in the chloroplasts, absorbs sunlight and helps plants produce glucose and oxygen. " +
  "The light-dependent reactions take place in the thylakoid membranes and produce ATP and NADPH. " +
  "The Calvin cycle then uses ATP and NADPH in the stroma to fix carbon dioxide into glucose. " +
  "Oxygen is released into the atmosphere as a by-product when water molecules are split.";
let items = [];
const L = "ABCD";

const words = () => (text.value.trim().match(/\S+/g) || []).length;
const updateCount = () => { $("count").textContent = words() + " words"; };
text.addEventListener("input", updateCount);
$("example").addEventListener("click", () => { text.value = EXAMPLE; updateCount(); text.focus(); });

function el(tag, cls, txt) { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

function answerText(it) {
  if (it.options) return `${L[it.correct_index]}. ${it.answer}`;
  return it.type === "tf" && it.answer === "False" ? `False. Correct statement: ${it.explanation}` : it.answer;
}

function render(note) {
  list.innerHTML = ""; list.classList.toggle("show", $("showAns").checked);
  items.forEach((it) => {
    const li = el("li");
    li.append(el("div", "q", (it.type === "tf" ? "True or false: " : "") + it.question));
    if (it.options) {
      const ul = el("ul", "opts");
      it.options.forEach((o, j) => ul.append(el("li", j === it.correct_index ? "opt right" : "opt", `${L[j]}. ${o}`)));
      li.append(ul);
    }
    li.append(el("div", "ans", "Answer: " + answerText(it)));
    if (it.score != null) { const m = el("div", "meta score"); m.innerHTML = "Quality score <b></b> / 100"; m.querySelector("b").textContent = it.score; li.append(m); }
    list.append(li);
  });
  if (note) list.prepend(Object.assign(el("p", "note", note), { style: "list-style:none" }));
}

function show({ status, error, ok }) {
  $("status").hidden = !status; $("status").textContent = status || "";
  $("error").hidden = !error; $("error").textContent = error || "";
  if (!ok) { list.innerHTML = ""; }
  $("actions").hidden = !ok;
  $("empty").hidden = !!(status || error || ok);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = "Request failed."; try { const d = await res.json(); if (typeof d.detail === "string") msg = d.detail; } catch {}
    throw new Error(msg);
  }
  return res;
}

go.addEventListener("click", async () => {
  const n = Number(document.querySelector('input[name="n"]:checked').value);
  go.disabled = true;
  show({ status: "Generating. The first request can take longer while the model warms up." });
  try {
    const res = await api("/api/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.value, num_questions: n, qtype: $("qtype").value, difficulty: $("difficulty").value }),
    });
    const data = await res.json(); items = data.items;
    show({ ok: true });
    render(items.length < n ? `Only ${items.length} of ${n} questions passed the quality filter. Add more text for more.` : "");
  } catch (e) { show({ error: e.message === "Failed to fetch" ? "Could not reach the server. Check that it is running." : e.message }); }
  finally { go.disabled = false; }
});

$("showAns").addEventListener("change", () => list.classList.toggle("show", $("showAns").checked));

$("file").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try {
    if (f.name.toLowerCase().endsWith(".txt")) text.value = await f.text();
    else {
      const fd = new FormData(); fd.append("file", f);
      text.value = (await (await api("/api/extract", { method: "POST", body: fd })).json()).text;
    }
    updateCount(); show({});
  } catch (err) { show({ error: err.message }); }
  e.target.value = "";
});

function plain() {
  return items.map((it, i) => {
    let s = `${i + 1}. ${it.type === "tf" ? "True or false: " : ""}${it.question}`;
    if (it.options) s += "\n" + it.options.map((o, j) => `   ${L[j]}. ${o}`).join("\n");
    return s;
  }).join("\n\n") + "\n\nAnswer key\n" + items.map((it, i) => `${i + 1}. ${answerText(it)}`).join("\n");
}
function save(blob, name) { const a = el("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); URL.revokeObjectURL(a.href); }

$("copy").addEventListener("click", async (e) => {
  await navigator.clipboard.writeText(plain());
  e.target.textContent = "Copied"; setTimeout(() => (e.target.textContent = "Copy"), 1500);
});
$("txt").addEventListener("click", () => save(new Blob([plain()], { type: "text/plain" }), "questions.txt"));
$("pdf").addEventListener("click", async () => {
  try {
    const res = await api("/api/export/pdf", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, include_answers: true, title: "Question Paper" }) });
    save(await res.blob(), "questions.pdf");
  } catch (err) { show({ error: err.message, ok: true }); render(); }
});
updateCount();

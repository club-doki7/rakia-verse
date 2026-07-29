#import "@preview/cuti:0.4.0": cn-fakebold as cuti

#let zh-fonts = ("Libertinus Serif", "Noto Serif SC", "Noto Serif CJK SC", "Scheherazade New")
#let fangsong-fonts = ("Libertinus Serif", "Zhuque Fangsong (technical preview)", "Scheherazade New")

#let part-page(title) = [
  #set page(paper: "iso-b5", numbering: "1")
  #align(
    center+horizon,
    text(
      font: zh-fonts,
      lang: "zh",
      size: 24pt,
      weight: "bold",
      heading(
        level: 1,
        numbering: none,
        supplement: "part",
        title
      )
    )
  )
]

#let chapter(xtag, id, title, body) = [
  #set page(paper: "iso-b5", numbering: "1")
  #set text(font: zh-fonts, lang: "zh", size: 11pt)
  #show heading.where(level: 1): set align(center)
  #counter(footnote).update(1)

  = #title #if id != none { label(id) }
  #v(1em)
  #body
]

#let beings = chapter.with("beings")
#let species = chapter.with("species")

#let section(xtag, id, body) = [
  #if id != none { label(id) } #body
]

#let being = section.with("being")
#let summary(body) = section("summary", none)[
  == 摘要

  #body
]

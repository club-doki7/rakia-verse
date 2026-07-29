#import "../librakia.typ": section

#let biology(body) = section("biology", none)[
  == 生理

  #body
]

#let reproduction(body) = section("reproduction", none)[
  == 繁殖

  #body
]

#let personality(body) = section("personality", none)[
  == 性格

  #body
]

#let society(body) = section("society", none)[
  == 社会

  #body
]

#let relations(body) = section("relations", none)[
  == 种族关系

  #body
]

#let faith(body) = section("faith", none)[
  == 信仰

  #body
]

#let sihr(body) = section("sihr", none)[
  == 魔术

  #body
]

#let variants(body) = section("variants", none)[
  == 变种

  #body
]

#let variant(id, title, body) = section("variant", id)[
  === #title

  #body
]

#let communication(body) = section("communication", none)[
  == 交流

  #body
]

#let shaman(body) = section("shaman", none)[
  == 萨满

  #body
]

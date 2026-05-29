export interface Verse {
  number: number;
  text: string;
  highlighted?: boolean;
}

export interface Section {
  heading: string;
  verses: Verse[];
}

export interface Book {
  name: string;
  testament: "Old" | "New";
  available?: boolean;
  chaptersCount: number;
}

export interface AIResponse {
  answer: string;
  verseReferences?: string[]; // E.g. ["19", "24"] to highlight verses discussed
  suggestions: string[];
}

export const booksList: Book[] = [
  // Old Testament
  { name: "Genesis", testament: "Old", chaptersCount: 50 },
  { name: "Exodus", testament: "Old", chaptersCount: 40 },
  { name: "Leviticus", testament: "Old", chaptersCount: 27 },
  { name: "Numbers", testament: "Old", chaptersCount: 36 },
  { name: "Deuteronomy", testament: "Old", chaptersCount: 34 },
  { name: "Joshua", testament: "Old", chaptersCount: 24 },
  { name: "Judges", testament: "Old", chaptersCount: 21 },
  { name: "Ruth", testament: "Old", chaptersCount: 4 },
  { name: "1 Samuel", testament: "Old", chaptersCount: 31 },
  { name: "2 Samuel", testament: "Old", chaptersCount: 24 },
  { name: "1 Kings", testament: "Old", chaptersCount: 22 },
  { name: "2 Kings", testament: "Old", chaptersCount: 25 },
  { name: "1 Chronicles", testament: "Old", chaptersCount: 29 },
  { name: "2 Chronicles", testament: "Old", chaptersCount: 36 },
  { name: "Ezra", testament: "Old", chaptersCount: 10 },
  { name: "Nehemiah", testament: "Old", chaptersCount: 13 },
  { name: "Esther", testament: "Old", chaptersCount: 10 },
  { name: "Job", testament: "Old", chaptersCount: 42 },
  { name: "Psalms", testament: "Old", chaptersCount: 150 },
  { name: "Proverbs", testament: "Old", chaptersCount: 31 },
  { name: "Ecclesiastes", testament: "Old", chaptersCount: 12 },
  { name: "Song of Solomon", testament: "Old", chaptersCount: 8 },
  { name: "Isaiah", testament: "Old", chaptersCount: 66 },
  { name: "Jeremiah", testament: "Old", chaptersCount: 52 },
  { name: "Lamentations", testament: "Old", chaptersCount: 5 },
  { name: "Ezekiel", testament: "Old", chaptersCount: 48 },
  { name: "Daniel", testament: "Old", chaptersCount: 12 },
  { name: "Hosea", testament: "Old", chaptersCount: 14 },
  { name: "Joel", testament: "Old", chaptersCount: 3 },
  { name: "Amos", testament: "Old", chaptersCount: 9 },
  { name: "Obadiah", testament: "Old", chaptersCount: 1 },
  { name: "Jonah", testament: "Old", chaptersCount: 4 },
  { name: "Micah", testament: "Old", chaptersCount: 7 },
  { name: "Nahum", testament: "Old", chaptersCount: 3 },
  { name: "Habakkuk", testament: "Old", chaptersCount: 3 },
  { name: "Zephaniah", testament: "Old", chaptersCount: 3 },
  { name: "Haggai", testament: "Old", chaptersCount: 2 },
  { name: "Zechariah", testament: "Old", chaptersCount: 14 },
  { name: "Malachi", testament: "Old", available: true, chaptersCount: 4 },

  // New Testament
  { name: "Matthew", testament: "New", available: true, chaptersCount: 28 },
  { name: "Mark", testament: "New", available: true, chaptersCount: 16 },
  { name: "Luke", testament: "New", available: true, chaptersCount: 24 },
  { name: "John", testament: "New", available: true, chaptersCount: 21 },
  { name: "Acts", testament: "New", chaptersCount: 28 },
  { name: "Romans", testament: "New", chaptersCount: 16 },
  { name: "1 Corinthians", testament: "New", chaptersCount: 16 },
  { name: "2 Corinthians", testament: "New", chaptersCount: 13 },
  { name: "Galatians", testament: "New", chaptersCount: 6 },
  { name: "Ephesians", testament: "New", chaptersCount: 6 },
  { name: "Philippians", testament: "New", chaptersCount: 4 },
  { name: "Colossians", testament: "New", chaptersCount: 4 },
  { name: "1 Thessalonians", testament: "New", chaptersCount: 5 },
  { name: "2 Thessalonians", testament: "New", chaptersCount: 3 },
  { name: "1 Timothy", testament: "New", chaptersCount: 6 },
  { name: "2 Timothy", testament: "New", chaptersCount: 4 },
  { name: "Titus", testament: "New", chaptersCount: 3 },
  { name: "Philemon", testament: "New", chaptersCount: 1 },
  { name: "Hebrews", testament: "New", chaptersCount: 13 },
  { name: "James", testament: "New", chaptersCount: 5 },
  { name: "1 Peter", testament: "New", chaptersCount: 5 },
  { name: "2 Peter", testament: "New", chaptersCount: 3 },
  { name: "1 John", testament: "New", chaptersCount: 5 },
  { name: "2 John", testament: "New", chaptersCount: 1 },
  { name: "3 John", testament: "New", chaptersCount: 1 },
  { name: "Jude", testament: "New", chaptersCount: 1 },
  { name: "Revelation", testament: "New", chaptersCount: 22 }
];

export const matthew1Content: Section[] = [
  {
    heading: "THE GENEALOGY OF JESUS CHRIST",
    verses: [
      { number: 1, text: "The book of the genealogy of Jesus Christ, the son of David, the son of Abraham." },
      { number: 2, text: "Abraham was the father of Isaac, and Isaac the father of Jacob, and Jacob the father of Judah and his brothers," },
      { number: 3, text: "and Judah the father of Perez and Zerah by Tamar, and Perez the father of Hezron, and Hezron the father of Ram," },
      { number: 4, text: "and Ram the father of Amminadab, and Amminadab the father of Nahshon, and Nahshon the father of Salmon," },
      { number: 5, text: "and Salmon the father of Boaz by Rahab, and Boaz the father of Obed by Ruth, and Obed the father of Jesse," },
      { number: 6, text: "and Jesse the father of David the king. And David was the father of Solomon by the wife of Uriah," },
      { number: 7, text: "and Solomon the father of Rehoboam, and Rehoboam the father of Abijah, and Abijah the father of Asaph," },
      { number: 8, text: "and Asaph the father of Jehoshaphat, and Jehoshaphat the father of Joram, and Joram the father of Uzziah," },
      { number: 9, text: "and Uzziah the father of Jotham, and Jotham the father of Ahaz, and Ahaz the father of Hezekiah," },
      { number: 10, text: "and Hezekiah the father of Manasseh, and Manasseh the father of Amos, and Amos the father of Josiah," },
      { number: 11, text: "and Josiah the father of Jechoniah and his brothers, at the time of the deportation to Babylon." },
      { number: 12, text: "And after the deportation to Babylon: Jechoniah was the father of Shealtiel, and Shealtiel the father of Zerubbabel," },
      { number: 13, text: "and Zerubbabel the father of Abiud, and Abiud the father of Eliakim, and Eliakim the father of Azor," },
      { number: 14, text: "and Azor the father of Zadok, and Zadok the father of Achim, and Achim the father of Eliud," },
      { number: 15, text: "and Eliud the father of Eleazar, and Eleazar the father of Matthan, and Matthan the father of Jacob," },
      { number: 16, text: "and Jacob the father of Joseph the husband of Mary, of whom Jesus was born, who is called Christ." },
      { number: 17, text: "So all the generations from Abraham to David were fourteen generations, and from David to the deportation to Babylon fourteen generations, and from the deportation to Babylon to the Christ fourteen generations." }
    ]
  },
  {
    heading: "THE BIRTH OF JESUS CHRIST",
    verses: [
      { number: 18, text: "Now the birth of Jesus Christ took place in this way. When his mother Mary had been betrothed to Joseph, before they came together she was found to be with child from the Holy Spirit." },
      { number: 19, text: "And her husband Joseph, being a just man and unwilling to put her to shame, resolved to divorce her quietly.", highlighted: true },
      { number: 20, text: "But as he considered these things, behold, an angel of the Lord appeared to him in a dream, saying, 'Joseph, son of David, do not fear to take Mary as your wife, for that which is conceived in her is from the Holy Spirit.'" },
      { number: 21, text: "She will bear a son, and you shall call his name Jesus, for he will save his people from their sins." },
      { number: 22, text: "All this took place to fulfill what the Lord had spoken by the prophet:" },
      { number: 23, text: "'Behold, the virgin shall conceive and bear a son, and they shall call his name Immanuel' (which means, God with us)." },
      { number: 24, text: "When Joseph woke from sleep, he did as the angel of the Lord commanded him: he took his wife," },
      { number: 25, text: "but knew her not until she had given birth to a son. And he called his name Jesus." }
    ]
  }
];

export const simulationQueries: Record<string, AIResponse> = {
  "what did joseph do next?": {
    answer: "After discovering Mary was with child, Joseph found himself in a deeply difficult position. As a 'just man' who loved Mary but sought to obey the law, he 'resolved to divorce her quietly' (v. 19) to shield her from public disgrace. However, when the angel of the Lord appeared to him in a dream, confirming the child was conceived of the Holy Spirit, Joseph immediately acted on faith. Upon waking, he 'did as the angel of the Lord commanded him' (v. 24) and took Mary as his wife.",
    verseReferences: ["19", "24"],
    suggestions: ["Explain verse 19 further", "Why is the genealogy of Jesus important in Matthew 1?"]
  },
  "explain verse 19 further": {
    answer: "In Matthew 1:19, the Greek word for 'just' (dikaios) refers to Joseph's upright character. He was a devout keeper of the Law, which normally demanded public exposure and justice for suspected infidelity. However, Joseph's righteousness is uniquely expressed through *mercy*. Rather than shaming Mary publicly (which could lead to severe social ostracism or even legal penalties), he chose a compassionate alternative: a private divorce before two witnesses. This highlights Joseph's deep integrity, showing that true righteousness under God is characterized by grace and loving-kindness.",
    verseReferences: ["19"],
    suggestions: ["What did Joseph do next?", "Why is the genealogy of Jesus important in Matthew 1?"]
  },
  "why is the genealogy of jesus important in matthew 1?": {
    answer: "The genealogy in Matthew 1 serves as a legal and theological bridge. Matthew, writing primarily for a Jewish audience, begins by tracing Jesus' lineage back to **Abraham** (establishing His Jewish identity and connection to God's covenant) and **David** (establishing His royal right to the throne of Israel as the promised Messiah). It proves that Jesus legally inherits the messianic promises.",
    verseReferences: ["1"],
    suggestions: ["What did Joseph do next?", "Explain verse 19 further"]
  }
};

export const defaultAIResponse = (query: string): AIResponse => {
  const norm = query.toLowerCase().trim();
  for (const k of Object.keys(simulationQueries)) {
    if (norm.includes(k) || k.includes(norm)) {
      return simulationQueries[k];
    }
  }
  return {
    answer: `Thank you for asking about Matthew 1. In verse 19, we see Joseph's reaction to Mary's pregnancy. He was a righteous man who cared deeply about both the Law and Mary's well-being. By resolving to divorce her quietly rather than put her to shame, he demonstrated tremendous integrity and grace under difficult circumstances, which prepared him for the angelic visitation that followed. Let me know if you would like to explore specific aspects of this passage further!`,
    suggestions: ["What did Joseph do next?", "Explain verse 19 further", "Why is the genealogy of Jesus important in Matthew 1?"]
  };
};

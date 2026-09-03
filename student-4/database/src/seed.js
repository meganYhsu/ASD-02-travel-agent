const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const dataDir = path.resolve(__dirname, "../data");
const dbPath = path.join(dataDir, "traveller-itinerary-details.sqlite");
const sqlite3Bin = process.env.SQLITE3_BIN || "/opt/anaconda3/bin/sqlite3";

const itineraries = [
  {
    destination: "Japan Test Seed",
    startDate: "2026-10-01",
    endDate: "2026-10-06",
    budget: "AUD 4200",
    travelGroup: "solo",
    travelStyle: "Sightseeing Travel",
    requirements: "Seed data for agentic loop validation",
    activities: [
      { dayNo: 1, date: "2026-10-01", location: "Tokyo", time: "09:00", cost: "AUD 25", note: "Arrival and easy city walk" },
      { dayNo: 1, date: "2026-10-01", location: "Tokyo", time: "13:00", cost: "AUD 40", note: "Lunch and museum visit" },
      { dayNo: 2, date: "2026-10-02", location: "Tokyo", time: "10:00", cost: "AUD 60", note: "Shibuya and Harajuku exploration" }
    ]
  },
  {
    destination: "Italy City Break",
    startDate: "2026-10-08",
    endDate: "2026-10-13",
    budget: "AUD 5100",
    travelGroup: "friends",
    travelStyle: "Cultural Travel",
    requirements: "Focus on galleries, food, and relaxed walking days",
    activities: [
      { dayNo: 1, date: "2026-10-08", location: "Rome", time: "10:00", cost: "AUD 30", note: "Historic center walk" },
      { dayNo: 2, date: "2026-10-09", location: "Rome", time: "12:30", cost: "AUD 55", note: "Museum and piazza lunch" },
      { dayNo: 3, date: "2026-10-10", location: "Florence", time: "09:15", cost: "AUD 70", note: "Train transfer and art district" }
    ]
  },
  {
    destination: "New Zealand Scenic Loop",
    startDate: "2026-10-15",
    endDate: "2026-10-20",
    budget: "AUD 6200",
    travelGroup: "family",
    travelStyle: "Road Trip",
    requirements: "Scenic drives with easy pacing and nature stops",
    activities: [
      { dayNo: 1, date: "2026-10-15", location: "Auckland", time: "09:30", cost: "AUD 20", note: "Arrival and waterfront stroll" },
      { dayNo: 2, date: "2026-10-16", location: "Rotorua", time: "11:00", cost: "AUD 45", note: "Geothermal park visit" },
      { dayNo: 3, date: "2026-10-17", location: "Taupo", time: "14:00", cost: "AUD 35", note: "Lake stop and picnic" }
    ]
  },
  {
    destination: "Thailand Food Trail",
    startDate: "2026-10-22",
    endDate: "2026-10-27",
    budget: "AUD 3300",
    travelGroup: "solo",
    travelStyle: "Slow Travel",
    requirements: "Prioritize markets, cooking classes, and local restaurants",
    activities: [
      { dayNo: 1, date: "2026-10-22", location: "Bangkok", time: "08:30", cost: "AUD 18", note: "River market breakfast" },
      { dayNo: 2, date: "2026-10-23", location: "Bangkok", time: "13:00", cost: "AUD 50", note: "Cooking class and lunch" },
      { dayNo: 3, date: "2026-10-24", location: "Chiang Mai", time: "10:30", cost: "AUD 40", note: "Old town food crawl" }
    ]
  },
  {
    destination: "Vietnam Heritage Route",
    startDate: "2026-10-29",
    endDate: "2026-11-03",
    budget: "AUD 3600",
    travelGroup: "friends",
    travelStyle: "Adventure Travel",
    requirements: "Blend old town exploration with one active outdoor day",
    activities: [
      { dayNo: 1, date: "2026-10-29", location: "Hanoi", time: "09:00", cost: "AUD 22", note: "Old quarter cycling tour" },
      { dayNo: 2, date: "2026-10-30", location: "Ninh Binh", time: "11:30", cost: "AUD 48", note: "Boat trip and limestone views" },
      { dayNo: 3, date: "2026-10-31", location: "Hanoi", time: "16:00", cost: "AUD 28", note: "Cafe and night market visit" }
    ]
  },
  {
    destination: "Portugal Coastal Escape",
    startDate: "2026-11-05",
    endDate: "2026-11-10",
    budget: "AUD 4700",
    travelGroup: "family-and-friends",
    travelStyle: "Leisure Travel",
    requirements: "Quiet coastal days with good food and short transfers",
    activities: [
      { dayNo: 1, date: "2026-11-05", location: "Lisbon", time: "10:00", cost: "AUD 24", note: "Arrival and tram ride" },
      { dayNo: 2, date: "2026-11-06", location: "Lisbon", time: "14:00", cost: "AUD 42", note: "Viewpoint and seafood lunch" },
      { dayNo: 3, date: "2026-11-07", location: "Cascais", time: "09:45", cost: "AUD 31", note: "Beachfront walking route" }
    ]
  },
  {
    destination: "Canada Mountain Route",
    startDate: "2026-11-12",
    endDate: "2026-11-17",
    budget: "AUD 6800",
    travelGroup: "large-group",
    travelStyle: "Adventure Travel",
    requirements: "Mountain scenery, easy hikes, and one rest day",
    activities: [
      { dayNo: 1, date: "2026-11-12", location: "Vancouver", time: "09:30", cost: "AUD 26", note: "Waterfront orientation walk" },
      { dayNo: 2, date: "2026-11-13", location: "Whistler", time: "12:00", cost: "AUD 64", note: "Peak gondola and lunch" },
      { dayNo: 3, date: "2026-11-14", location: "Banff", time: "10:15", cost: "AUD 58", note: "Lake viewpoint and town stroll" }
    ]
  },
  {
    destination: "Iceland Ring Road Lite",
    startDate: "2026-11-19",
    endDate: "2026-11-24",
    budget: "AUD 7200",
    travelGroup: "solo",
    travelStyle: "Sightseeing Travel",
    requirements: "Natural highlights, flexible pacing, and weather alternatives",
    activities: [
      { dayNo: 1, date: "2026-11-19", location: "Reykjavik", time: "11:00", cost: "AUD 34", note: "City center orientation" },
      { dayNo: 2, date: "2026-11-20", location: "Golden Circle", time: "09:00", cost: "AUD 72", note: "Waterfalls and geothermal stops" },
      { dayNo: 3, date: "2026-11-21", location: "Vik", time: "15:00", cost: "AUD 46", note: "Black sand beach visit" }
    ]
  },
  {
    destination: "Spain Art and Tapas",
    startDate: "2026-11-26",
    endDate: "2026-12-01",
    budget: "AUD 4900",
    travelGroup: "friends",
    travelStyle: "Cultural Travel",
    requirements: "Art museums, late dinners, and neighborhood walks",
    activities: [
      { dayNo: 1, date: "2026-11-26", location: "Madrid", time: "10:00", cost: "AUD 28", note: "Museum district morning" },
      { dayNo: 2, date: "2026-11-27", location: "Madrid", time: "19:00", cost: "AUD 36", note: "Tapas crawl" },
      { dayNo: 3, date: "2026-11-28", location: "Seville", time: "11:30", cost: "AUD 52", note: "Cathedral and old town walk" }
    ]
  },
  {
    destination: "South Korea Urban Mix",
    startDate: "2026-12-03",
    endDate: "2026-12-08",
    budget: "AUD 5400",
    travelGroup: "solo",
    travelStyle: "Fast-Paced Travel",
    requirements: "Mix city sights with food stops and evening neighborhoods",
    activities: [
      { dayNo: 1, date: "2026-12-03", location: "Seoul", time: "08:45", cost: "AUD 21", note: "Arrival and palace district" },
      { dayNo: 2, date: "2026-12-04", location: "Seoul", time: "13:00", cost: "AUD 44", note: "Design district and lunch" },
      { dayNo: 3, date: "2026-12-05", location: "Busan", time: "17:30", cost: "AUD 39", note: "Night market and coastal walk" }
    ]
  }
];

function escapeSql(value) {
  return String(value).replaceAll("'", "''");
}

function buildSeedSql() {
  const statements = [
    "PRAGMA foreign_keys = ON;",
    "BEGIN;",
    "DELETE FROM activity;",
    "DELETE FROM itinerary;"
  ];

  for (const itinerary of itineraries) {
    statements.push(`
      INSERT INTO itinerary (
        destination,
        start_date,
        end_date,
        budget,
        travel_group,
        travel_style,
        requirements
      ) VALUES (
        '${escapeSql(itinerary.destination)}',
        '${escapeSql(itinerary.startDate)}',
        '${escapeSql(itinerary.endDate)}',
        '${escapeSql(itinerary.budget)}',
        '${escapeSql(itinerary.travelGroup)}',
        '${escapeSql(itinerary.travelStyle)}',
        '${escapeSql(itinerary.requirements)}'
      );
    `.trim());

    const itineraryRef = `(
      SELECT itinerary_id
      FROM itinerary
      WHERE destination = '${escapeSql(itinerary.destination)}'
        AND start_date = '${escapeSql(itinerary.startDate)}'
      LIMIT 1
    )`;

    for (const activity of itinerary.activities) {
      statements.push(`
        INSERT INTO activity (
          itinerary_id,
          day_no,
          date,
          location,
          time,
          cost,
          note
        ) VALUES (
          ${itineraryRef},
          ${activity.dayNo},
          '${escapeSql(activity.date)}',
          '${escapeSql(activity.location)}',
          '${escapeSql(activity.time)}',
          '${escapeSql(activity.cost)}',
          '${escapeSql(activity.note)}'
        );
      `.trim());
    }
  }

  statements.push("COMMIT;");
  return statements.join("\n");
}

function main() {
  fs.mkdirSync(dataDir, { recursive: true });

  const sql = buildSeedSql();
  execFileSync(sqlite3Bin, [dbPath], {
    input: sql,
    stdio: ["pipe", "inherit", "inherit"]
  });

  const verifySql = [
    "SELECT COUNT(*) FROM itinerary;",
    "SELECT COUNT(*) FROM activity;"
  ].join("\n");

  const verification = execFileSync(sqlite3Bin, [dbPath], {
    input: verifySql,
    encoding: "utf8"
  }).trim().split(/\r?\n/);

  console.log(`Seeded ${verification[0]} itinerary rows and ${verification[1]} activity rows.`);
}

main();

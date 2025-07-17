import { prisma } from "@/app";
import { assetBuckets } from "./Darius.model";

export const getMostRecentFiles = async (date: string): Promise<any[]> => {
  try {
    // Get the most recent research records from the database
    const latestFiles = await prisma.research.findMany({
      orderBy: {
        created_at: 'desc'
      },
      where: {
        created_at: {
          lte: new Date(date)
        }
      },
      take: 1,
      select: {
        id: true,
        title: true,
        type: true,
        plain_text: true,
        created_at: true,
        updated_at: true
      }
    });

    console.log(`  📄 Found ${latestFiles.length} research files`);

    return latestFiles;
  } catch (error) {
    console.error('❌ [getMostRecentFiles] Database error:', error instanceof Error ? error.message : 'Unknown error');
    return [];
  }
};

// findLatestMacroData functonn gets the 3 latest macro files and returns the text back in an object list so 
//  {"Macro Scouting Report": "text", "Leadoff Morning Note": "text", "Around The Horn": "text"}
// We filter by type the 3 tyles are leadoff_morning_note, around_the_horn macro_scouting_report and we take 1 of each
export const findLatestMacroData = async () => {
  return prisma.research.findMany({
    orderBy: {
      created_at: 'desc'
    },
    take: 3,
    select: {
      title: true,
      plain_text: true
    }
  })
}

export const getListOfTradableAssets = async (date: string) => {
  // Log function entry
  console.log('🏦 [Darius Controller] getListOfTradableAssets called');
  console.log(`  📅 Date: ${date}`);

  const startTime = Date.now();

  try {
    console.log('  🔍 Fetching research data...');
    const files = await getMostRecentFiles(date);
    
    if (files.length === 0) {
      console.log('  ⚠️  No files found for the given date');
      return [];
    }

    console.log('  🔍 Extracting top markets...');
    const topMarkets = extractTopMarkets(files[0].plain_text);
    console.log(`  📊 Found ${topMarkets.length} top markets: ${topMarkets.join(', ')}`);

    console.log('  🔍 Mapping to asset buckets...');
    const tradableAssets = topMarkets.map(market => {
      const bucket = assetBuckets[market as keyof typeof assetBuckets];
      return bucket || [];
    }).flat();

    const uniqueAssets = [...new Set(tradableAssets)];
    
    const duration = Date.now() - startTime;
    console.log(`✅ [Darius Controller] Found ${uniqueAssets.length} unique assets in ${duration}ms`);

    return uniqueAssets;

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`❌ [Darius Controller] Failed in ${duration}ms:`, error instanceof Error ? error.message : 'Unknown error');
    throw error;
  }
}

function extractTopMarkets(text: string) {
  // 1. Normalize whitespace (collapse newlines/tabs into single spaces)
  const clean = text.replace(/\s+/g, ' ').trim();

  // 2. Find the clause after "considerations ... are:"
  const re = /considerations.*?are:(.*?)(?:\.|$)/i;
  const match = clean.match(re);
  if (!match) return [];

  // 3. Grab that body, split on commas (and optional leading "and ")
  const body = match[1].trim();
  const parts = body.split(/,\s*(?:and\s*)?/i);

  // 4. For each part containing ">", take what's before the first ">"
  const winners = parts
    .map(part => {
      const idx = part.indexOf('>');
      if (idx === -1) return null;
      // slice left of '>', trim punctuation
      return part
        .slice(0, idx)
        .replace(/[.,]$/, '')  // remove trailing comma/period if any
        .trim();
    })
    .filter(Boolean);

  return winners;
}

const REGIMES = ['GOLDILOCKS', 'INFLATION', 'REFLATION', 'DEFLATION'];


export const getRegime = async (date: string) => {

  const files = await getMostRecentFiles(date)

  const regime = extractRegime(files[0].plain_text)

  return regime
}


export function extractRegime(text: string) {
  // Try to grab whatever follows "Market Regime:"
  const re = /Market Regime:\s*([A-Za-z]+)/i;
  const m = text.match(re);
  if (m) {
    const candidate = m[1].toUpperCase();
    if (REGIMES.includes(candidate)) return candidate;
  }

  // Fallback: scan for any of the known regime names
  const upper = text.toUpperCase();
  for (const r of REGIMES) {
    if (upper.includes(r)) return r;
  }

  return null;
}


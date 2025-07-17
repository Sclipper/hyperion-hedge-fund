import { openai } from '@ai-sdk/openai'
import fs from 'fs'
import path from 'path'
import { generateText, tool } from 'ai'
import { macroSystemPrompt } from './Darius.model'
import { date, z } from 'zod'
import { extractRegime, findLatestMacroData, getListOfTradableAssets, getRegime } from './Darius.controller'
import { hyperionAgentsMCP } from '@/app'

hyperionAgentsMCP.tool(
  'talk_to_darius',
  'Get any information from the Darius the macro agent.',
  {
    prompt: z.string().describe('The prompt to get information from the macro agent'),
  },
  async ({ prompt }) => {
    const data = await macroAnalysisAgent(prompt)
    console.log('data', data)
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(data),
        },

      ],
    }
  },
)


hyperionAgentsMCP.tool(
  'get_list_of_tradable_assets',
  'Get a list of tradable assets based on the macro data.',
  {
    date: z.string().describe('The date allows you to go back in time and get the list of tradable assets for a point in the past').optional(),
  },
  {
    output: z.object({
      content: z.array(z.object({
        type: z.literal('text'),
        text: z.string().describe('{"regime": "GOLDILOCKS" | "INFLATION" | "REFLATION" | "DEFLATION", "assets": ["AAPL", "TSLA", "NVDA", etc...]}'),
      })).describe('The list of tradable assets'),
    }),
  },
  async ({ date }) => {
    const tradableAssets = await getListOfTradableAssets(date || new Date().toISOString())
    const regime = await getRegime(date || new Date().toISOString())

    const data = {
      regime,
      assets: tradableAssets
    }
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(data),
        },
      ],
    }
  },
)

export const macroAnalysisAgent = async (prompt: string) => {
  const { text } = await generateText({
    model: openai('gpt-4o-mini'),
    messages: [
      {
        role: 'system',
        content: macroSystemPrompt,
      },

      {
        role: 'user',
        content: prompt,
      },
    ],
    tools: {
      read_latest_macro_data: tool({
        description: 'Read the latest ATH, MSR and LMN data from their respective folders',
        parameters: z.object({}),
        execute: async () => findLatestMacroData(),
      }),
    },
    maxSteps: 10,
  })

  console.log('text', text)
  return text
}
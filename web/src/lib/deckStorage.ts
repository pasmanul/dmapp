export interface DeckJson {
  name: string
  cards: Array<{ cardId: string; count: number }>
}

/** decks/ サブフォルダを取得または作成する */
async function getDecksDir(
  dirHandle: FileSystemDirectoryHandle,
): Promise<FileSystemDirectoryHandle> {
  return dirHandle.getDirectoryHandle('decks', { create: true })
}

/** decks/ 内の *.json ファイル名（拡張子なし）一覧を返す */
export async function listDeckFiles(
  dirHandle: FileSystemDirectoryHandle,
): Promise<string[]> {
  const decksDir = await getDecksDir(dirHandle)
  const names: string[] = []
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for await (const [name] of (decksDir as any).entries()) {
    if (typeof name === 'string' && name.endsWith('.json')) {
      names.push(name.slice(0, -5))
    }
  }
  return names.sort()
}

/**
 * ファイル名（拡張子なし）を指定してデッキを読み込む。
 * Python 版の旧フォーマット（id フィールド）にも対応する。
 */
export async function readDeckFile(
  dirHandle: FileSystemDirectoryHandle,
  filename: string,
): Promise<DeckJson> {
  const decksDir = await getDecksDir(dirHandle)
  const fileHandle = await decksDir.getFileHandle(`${filename}.json`)
  const file = await fileHandle.getFile()
  const raw = JSON.parse(await file.text())

  // Python 版互換: cards[] の各エントリが id を持ち cardId を持たない場合に変換
  const cards = (raw.cards ?? []).map((entry: Record<string, unknown>) => ({
    cardId: (entry.cardId ?? entry.id) as string,
    count: (entry.count as number) ?? 1,
  }))

  return { name: (raw.name as string) ?? filename, cards }
}

/** デッキを filename.json として decks/ フォルダに書き込む */
export async function writeDeckFile(
  dirHandle: FileSystemDirectoryHandle,
  filename: string,
  deck: DeckJson,
): Promise<void> {
  const decksDir = await getDecksDir(dirHandle)
  const fileHandle = await decksDir.getFileHandle(`${filename}.json`, {
    create: true,
  })
  const writable = await fileHandle.createWritable()
  await writable.write(JSON.stringify(deck, null, 2))
  await writable.close()
}

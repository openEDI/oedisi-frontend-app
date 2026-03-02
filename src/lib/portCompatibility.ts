import typeHierarchyJson from './typeHierarchy.json'

const typeHierarchy: Record<string, string | null> = typeHierarchyJson

function isSubtype(src: string | null, tgt: string | null): boolean {
    if (src === tgt) { return true }
    let current: string | null = src
    while (current != null && current in typeHierarchy && typeHierarchy[current] != null) {
        current = typeHierarchy[current]
        if (current === tgt) {
            return true
        }
    }
    return false
}

function normalizeType(type: string | null): string | null {
    if (type === "") {
        return null
    }
    return type
}

export function isCompatible(src: string | null, tgt: string | null): boolean {
    return isSubtype(normalizeType(src), normalizeType(tgt)) ||
        isSubtype(normalizeType(tgt), normalizeType(src))
}

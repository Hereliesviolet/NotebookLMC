Bewerte die Relevanz jedes Chunks für die Nutzerfrage auf einer Skala von 0 bis 5.

Gib ausschließlich JSON zurück.

Nutzerfrage:
{{question}}

Chunks:
{{chunks}}

Output:
{
  "ranked_chunks": [
    {
      "chunk_id": "string",
      "score": 0,
      "reason": "string"
    }
  ]
}

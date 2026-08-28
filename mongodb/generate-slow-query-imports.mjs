import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const documentCount = 50_000;
const outputDirectory = join(dirname(fileURLToPath(import.meta.url)), 'mongo-express-imports');

mkdirSync(outputDirectory, { recursive: true });

function extendedJsonDate(value) {
  return { $date: value.toISOString() };
}

function writeFixture(fileName, createDocument) {
  const documents = Array.from({ length: documentCount }, (_, index) => createDocument(index));
  const outputPath = join(outputDirectory, fileName);
  writeFileSync(outputPath, `${JSON.stringify(documents)}\n`, 'utf8');
  console.log(`wrote ${documents.length} documents to ${outputPath}`);
}

writeFixture('slow_query_claim_lookup.json', (index) => ({
  exerciseId: 'SLOW-QUERY-01',
  claimNumber: `CLM-${String(index).padStart(6, '0')}`,
  customerId: `CUS-${String(index % 10_000).padStart(5, '0')}`,
  status: index % 4 === 0 ? 'OPEN' : 'CLOSED',
  lossType: ['collision', 'theft', 'water', 'fire'][index % 4],
}));

writeFixture('slow_query_claim_queue.json', (index) => ({
  exerciseId: 'SLOW-QUERY-02',
  claimNumber: `QUEUE-${String(index).padStart(6, '0')}`,
  status: index % 5 === 0 ? 'OPEN' : 'CLOSED',
  priority: 1 + (index % 5),
  reportedAt: extendedJsonDate(new Date(Date.UTC(2026, 0, 1, 0, index))),
  adjusterRegion: ['NORTH', 'SOUTH', 'EAST', 'WEST'][index % 4],
}));

const riskStates = ['CA', 'NV', 'AZ', 'OR'];
writeFixture('slow_query_policy_renewals.json', (index) => ({
  exerciseId: 'SLOW-QUERY-03',
  policyNumber: `POL-${String(index).padStart(6, '0')}`,
  carrierId: `CAR-${String(index % 10).padStart(2, '0')}`,
  status: index % 5 === 0 ? 'CANCELLED' : 'ACTIVE',
  renewalDate: extendedJsonDate(new Date(Date.UTC(2026, 0, 1 + (index % 365)))),
  risk: {
    state: riskStates[index % riskStates.length],
    line: index % 2 === 0 ? 'AUTO' : 'HOME',
  },
}));

writeFixture('slow_query_provider_payments.json', (index) => ({
  exerciseId: 'SLOW-QUERY-04',
  paymentReference: `PAY-${String(index).padStart(6, '0')}`,
  provider: {
    npi: String(1_000_000_000 + (index % 2_000)),
    name: `Provider ${index % 2_000}`,
  },
  status: index % 3 === 0 ? 'PENDING_REVIEW' : 'APPROVED',
  submittedAt: extendedJsonDate(new Date(Date.UTC(2026, 7, 1, 0, index))),
  amount: { $numberDecimal: `${100 + (index % 25_000)}.00` },
}));

writeFixture('slow_query_investigation_tags.json', (index) => {
  const investigationTags = ['standard-review', index % 2 === 0 ? 'auto' : 'property'];
  if (index % 4_000 === 0) investigationTags.push('catastrophe-watch');

  return {
    exerciseId: 'SLOW-QUERY-05',
    claimNumber: `TAG-${String(index).padStart(6, '0')}`,
    status: index % 4 === 0 ? 'OPEN' : 'CLOSED',
    investigationTags,
    updatedAt: extendedJsonDate(new Date(Date.UTC(2026, 7, 1, 0, index))),
  };
});

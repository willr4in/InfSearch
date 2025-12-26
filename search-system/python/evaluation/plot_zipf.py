import psycopg2
import matplotlib.pyplot as plt
import os

os.makedirs('docs/diagrams', exist_ok=True)

conn = psycopg2.connect('host=db user=infsearch password=infsearch dbname=infsearch')
cur = conn.cursor()
cur.execute('SELECT rank, freq, expected FROM zipf_statistics ORDER BY rank')
rows = cur.fetchall()
ranks = [r for (r,_,_) in rows]
freqs = [f for (_,f,_) in rows]
expected = [e for (_,_,e) in rows]

plt.figure(figsize=(8,6))
plt.loglog(ranks, freqs, marker='.', label='actual')
plt.loglog(ranks, expected, marker='.', label='theoretical')
plt.xlabel('rank')
plt.ylabel('frequency')
plt.legend()
plt.title('Zipf distribution')
plt.savefig('docs/diagrams/zipf_plot.png')
print('Saved docs/diagrams/zipf_plot.png')

# save simple report
cur.execute("SELECT value FROM zipf_params WHERE name='alpha'")
alpha_row = cur.fetchone()
alpha = alpha_row[0] if alpha_row else None
with open('docs/zipf_report.txt','w') as f:
    f.write(f'Estimated alpha: {alpha}\n')
    f.write(f'Recorded points: {len(ranks)}\n')

print('Report saved to docs/zipf_report.txt')
cur.close()
conn.close()

        # Boss contact checks should use the readable focal hitbox rather than
        # the full sprite rectangle. This makes the attack feel intentional and
        # reduces accidental contact on the boss edges.
        boss_contact = (self.boss.weakspot() if self.boss.state == 'stunned'
                        else self.boss.body_hitbox())
        if self.boss.active and self.player.colliderect(boss_contact):
            can_stomp = self.boss.can_stomp(
                self.player, previous_bottom, self.velocity_y)
            if can_stomp and self.boss.stomp():
                # Place the feet clear of the new roar hitbox before the next
                # frame. The bounce alone left several overlapping frames and
                # caused an immediate retaliatory hit after a valid stomp.
                self.player.bottom = self.boss.rect.top-4
                self.velocity_y = -470
                self.y = float(self.player.y)
                self.on_ground = False
                self.invincible = max(self.invincible, 0.75)
                self.audio.play('defeat')
                if self.boss.defeated:
                    self.score += self.boss.SCORE
                    self.feedback.emit(self.boss.rect.midtop,
                                       f'보스 격파! +{self.boss.SCORE}', (255, 224, 112))
                    self.progress.save(self)
                else:
                    self.feedback.emit(self.boss.rect.midtop,
                                       f'보스 타격 {self.boss.hits}/{self.boss.MAX_HITS}',
                                       (255, 224, 112))
            elif not self.invincible and self.boss.state != 'stunned':
                self.combat.hit(self.player, self.boss)
                self.feedback.emit(self.player.midtop, '보스에게 피격!', (255, 133, 125))
                return
        skua_projectile_hit = (not self.invincible and self.skua_boss.active
                               and self.skua_boss.snowball_hits(self.player))
        skua_body_hit = (not self.invincible and self.skua_boss.can_damage_player()
                         and self.player.colliderect(self.skua_boss.body_hitbox()))
        if skua_projectile_hit or skua_body_hit:
            self.combat.hit(self.player, self.skua_boss)
            self.feedback.emit(self.player.midtop, '갈매기에게 피격!', (255, 133, 125))
            return
